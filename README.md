# setlist-tube.fm

Paste a [setlist.fm](https://www.setlist.fm) show link and get a YouTube
playlist of everything that was played.

1. The setlist is fetched from the setlist.fm API.
2. Each song is searched on YouTube Music (no login) and fuzzy-matched on
   title and artist. Live/remaster/feat. noise is ignored, covers fall back to
   the original artist, and tape intros/outros are skipped.
3. The matches become a temporary YouTube playlist link
   (`youtube.com/watch_videos?video_ids=…`). No account needed.

Low-confidence matches are flagged as **unsure**; songs that can't be found are
listed but left out.

## Running locally

Needs [uv](https://docs.astral.sh/uv/) and a free
[setlist.fm API key](https://www.setlist.fm/settings/api).

```bash
uv sync
```

```bash
SETLISTFM_API_KEY=your-key uv run uvicorn setlist_tube.web:app --reload
```

Then open http://127.0.0.1:8000. A JSON version lives at
`/api/setlist?url=…` (docs at `/api/docs`).

## Development

```bash
uv run pre-commit install   # lint/format/type-check on every commit
```

| Check  | Command                     |
| ------ | --------------------------- |
| Lint   | `uv run ruff check .`       |
| Format | `uv run ruff format .`      |
| Types  | `uv run mypy`               |
| Tests  | `uv run pytest`             |

CI (`.github/workflows/ci.yml`) runs all four on every pull request and on
`main`. Dependabot keeps Python packages and Actions up to date.

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

### Extension points

Not built yet, but the code is shaped for them:

- **Other catalogs (Spotify):** implement `Catalog.search` in `catalog.py`.
- **Save to the user's account (YouTube Music / Spotify):** add an exporter
  next to `playlist.py`; it takes the matched `Track`s.
- **Sharing / history:** `SetlistResult` is a plain dataclass, easy to
  persist once there's a database.

## Deployment (Render, free plan)

One-time setup:

1. In Render, **New → Blueprint**, pick this repo. It reads `render.yaml`.
2. Set `SETLISTFM_API_KEY` in the service's **Environment** tab.
3. In the service's **Settings**, copy the **Deploy Hook** URL.
4. In GitHub, **Settings → Secrets and variables → Actions**, add it as
   `RENDER_DEPLOY_HOOK_URL`.
5. Recommended: **Settings → Branches**, protect `main` and require the
   "Lint, type-check, test" check, so merges only land when CI is green.

From then on, every merge to `main` runs CI and, if it passes, deploys.

The free plan sleeps after 15 minutes idle, so the first request after a
break takes 30-60 seconds.

## Caveats

- YouTube Music search uses the unofficial
  [ytmusicapi](https://github.com/sigma67/ytmusicapi), which can break when
  YouTube changes things. YouTube may also throttle searches from cloud IPs.
- `watch_videos` links are undocumented and cap at 50 videos per link (longer
  shows get several links). They open in YouTube, not the YouTube Music app.

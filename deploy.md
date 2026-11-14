# Build and deploy

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

## Deployment (Render, free plan)

The live app is at https://setlist-tube.onrender.com. The service is described
in `render.yaml`.

One-time setup:

1. In Render, **New → Blueprint**, pick this repo. It reads `render.yaml`.
2. Set `SETLISTFM_API_KEY` in the service's **Environment** tab.
3. In the service's **Settings**, copy the **Deploy Hook** URL.
4. In GitHub, **Settings → Secrets and variables → Actions**, add it as
   `RENDER_DEPLOY_HOOK_URL`.
5. Recommended: **Settings → Branches**, protect `main` and require the
   "Lint, type-check, test" check, so merges only land when CI is green.

From then on, every merge to `main` runs CI and, if it passes, deploys exactly
that commit. Render's own auto-deploy is off.

The free plan sleeps after 15 minutes idle, so the first request after a
break takes 30-60 seconds.

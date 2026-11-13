# setlist-tube.fm

Paste a [setlist.fm](https://www.setlist.fm) show link and get a YouTube
playlist of everything that was played.

## Development

Needs [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

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

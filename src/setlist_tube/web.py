"""FastAPI app: one page to paste a setlist.fm link, plus a small JSON API."""

from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from setlist_tube.catalog import YouTubeMusicCatalog
from setlist_tube.config import Settings
from setlist_tube.service import SetlistResult, SetlistService
from setlist_tube.setlistfm import (
    InvalidSetlistUrl,
    SetlistError,
    SetlistFmClient,
    SetlistNotFound,
)

HERE = Path(__file__).parent
templates = Jinja2Templates(directory=HERE / "templates")

app = FastAPI(title="setlist-tube.fm", docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


@lru_cache
def get_service() -> SetlistService:
    settings = Settings.from_env()
    if not settings.setlistfm_api_key:
        raise HTTPException(503, "Server is missing its setlist.fm API key.")
    return SetlistService(SetlistFmClient(settings.setlistfm_api_key), YouTubeMusicCatalog())


Service = Annotated[SetlistService, Depends(get_service)]


def _status_for(err: SetlistError) -> int:
    if isinstance(err, InvalidSetlistUrl):
        return 400
    if isinstance(err, SetlistNotFound):
        return 404
    return 502


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"url": "", "result": None})


@app.get("/show", response_class=HTMLResponse)
def show(
    request: Request,
    service: Service,
    url: Annotated[str, Query(max_length=500)] = "",
) -> HTMLResponse:
    context: dict[str, Any] = {"url": url, "result": None, "error": None}
    status = 200
    try:
        context["result"] = service.build(url)
    except SetlistError as err:
        context["error"] = str(err)
        status = _status_for(err)
    return templates.TemplateResponse(request, "index.html", context, status_code=status)


@app.get("/api/setlist")
def api_setlist(
    service: Service,
    url: Annotated[str, Query(max_length=500)],
) -> dict[str, Any]:
    try:
        result: SetlistResult = service.build(url)
    except SetlistError as err:
        raise HTTPException(_status_for(err), str(err)) from err
    return {
        "setlist": asdict(result.setlist) | {"title": result.setlist.title},
        "matches": [asdict(m) for m in result.matches],
        "skipped": [asdict(s) for s in result.skipped],
        "playlist_urls": result.playlist_urls,
    }

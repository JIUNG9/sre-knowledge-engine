"""
Confluence-compatible mock API for Aegis demo.

Implements a minimal subset of Atlassian Confluence Cloud REST API
to allow Aegis wiki/runbook features to function without real Confluence.

Endpoints:
  GET /rest/api/content              — list all pages (paginated)
  GET /rest/api/content/{id}         — single page
  GET /rest/api/space                — list spaces
  GET /healthz                       — healthcheck

20 canned runbook pages with intentional staleness (2023, 2025, current).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="Aegis Demo Confluence Mock", version="0.1.0")

_PAGES_FILE = Path(__file__).parent / "pages.json"
with _PAGES_FILE.open() as f:
    _DATA: dict[str, Any] = json.load(f)

_PAGES: list[dict[str, Any]] = _DATA["pages"]
_SPACES: list[dict[str, Any]] = _DATA["spaces"]


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "pages": str(len(_PAGES)), "spaces": str(len(_SPACES))}


@app.get("/rest/api/content")
def list_content(
    limit: int = Query(25, ge=1, le=100),
    start: int = Query(0, ge=0),
    spaceKey: str | None = None,
    type: str = "page",
) -> JSONResponse:
    filtered = _PAGES
    if spaceKey:
        filtered = [p for p in filtered if p.get("space", {}).get("key") == spaceKey]
    page = filtered[start : start + limit]
    return JSONResponse(
        {
            "results": page,
            "start": start,
            "limit": limit,
            "size": len(page),
            "_links": {
                "base": "http://confluence-mock:8090",
                "context": "/wiki",
                "self": f"/rest/api/content?start={start}&limit={limit}",
            },
        }
    )


@app.get("/rest/api/content/{page_id}")
def get_page(page_id: str) -> dict[str, Any]:
    for p in _PAGES:
        if p["id"] == page_id:
            return p
    raise HTTPException(status_code=404, detail=f"Page {page_id} not found")


@app.get("/rest/api/space")
def list_spaces(limit: int = 25, start: int = 0) -> JSONResponse:
    page = _SPACES[start : start + limit]
    return JSONResponse(
        {
            "results": page,
            "start": start,
            "limit": limit,
            "size": len(page),
        }
    )

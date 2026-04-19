"""FastAPI router for the Aegis LLM Wiki Engine.

Provides the HTTP surface for Layer 1 (Living Knowledge Base). Heavy workflows
(sync, publish, vault-wide lint) run via BackgroundTasks so clients get a job
id back immediately and can poll for completion. Long-running Claude calls
(ingest, query) run inline because the caller is almost always waiting for
the returned page/answer.
"""

from __future__ import annotations

import json
import logging
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from pydantic import BaseModel, Field

from config import settings
from wiki import (
    Contradiction,
    ContradictionDetector,
    ContradictionReport,
    DEFAULT_RULES,
    Ingester,
    Publisher,
    PublisherConfig,
    PublishResult,
    SignozConfig,
    SignozSync,
    SignozSyncResult,
    Source,
    StalenessLinter,
    StalenessReport,
    Synthesizer,
    WikiEngine,
    WikiEngineConfig,
    WikiPage,
)
from wiki import ConfluenceConfig, ConfluenceSync, ConfluenceSyncResult

logger = logging.getLogger("aegis.wiki.api")

router = APIRouter(prefix="/api/v1/wiki", tags=["Wiki"])


# ---------------------------------------------------------------------------
# Job tracking (background tasks)
# ---------------------------------------------------------------------------
# Jobs are in-memory only — good enough for a single-process dev deployment.
# A production deployment would back this with Redis so multiple workers can
# share state and jobs survive restarts.

_JOBS: dict[str, dict[str, Any]] = {}


def _new_job(kind: str) -> str:
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {
        "id": job_id,
        "kind": kind,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
    }
    return job_id


def _mark_started(job_id: str) -> None:
    job = _JOBS.get(job_id)
    if job is not None:
        job["status"] = "running"
        job["started_at"] = datetime.now(timezone.utc).isoformat()


def _mark_finished(job_id: str, result: Any) -> None:
    job = _JOBS.get(job_id)
    if job is not None:
        job["status"] = "succeeded"
        job["finished_at"] = datetime.now(timezone.utc).isoformat()
        job["result"] = result


def _mark_failed(job_id: str, error: str) -> None:
    job = _JOBS.get(job_id)
    if job is not None:
        job["status"] = "failed"
        job["finished_at"] = datetime.now(timezone.utc).isoformat()
        job["error"] = error


# ---------------------------------------------------------------------------
# Dependency: singleton WikiEngine
# ---------------------------------------------------------------------------
# Built lazily so boot succeeds even when the Anthropic key is absent — only
# endpoints that actually need the engine raise 503.

_engine_singleton: WikiEngine | None = None


def _build_engine() -> WikiEngine:
    if WikiEngine is None or WikiEngineConfig is None:
        raise HTTPException(status_code=503, detail="Wiki engine module not available")
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")
    try:
        from anthropic import AsyncAnthropic
    except ImportError as exc:
        raise HTTPException(
            status_code=503, detail=f"anthropic sdk not installed: {exc}"
        ) from exc

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    config = WikiEngineConfig(
        vault_root=settings.wiki_vault_root,
        synthesis_model=settings.wiki_synthesis_model,
        contradiction_model=settings.wiki_contradiction_model,
        stale_threshold_days=settings.wiki_stale_threshold_days,
        archive_threshold_days=settings.wiki_archive_threshold_days,
    )
    return WikiEngine(anthropic_client=client, config=config)


def get_engine() -> WikiEngine:
    """FastAPI dependency returning the process-wide WikiEngine singleton."""
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = _build_engine()
    return _engine_singleton


def _get_anthropic_client() -> Any:
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")
    try:
        from anthropic import AsyncAnthropic
    except ImportError as exc:
        raise HTTPException(
            status_code=503, detail=f"anthropic sdk not installed: {exc}"
        ) from exc
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


# ---------------------------------------------------------------------------
# Response / request models
# ---------------------------------------------------------------------------


class IngestURLRequest(BaseModel):
    source_url: str = Field(..., min_length=1, description="Remote URL to fetch")


class WikiPageResponse(BaseModel):
    slug: str
    title: str
    type: str | None = None
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    body: str
    path: str | None = None


class PageListItem(BaseModel):
    slug: str
    title: str
    type: str | None = None
    freshness: str | None = None
    updated_at: str | None = None
    tags: list[str] = Field(default_factory=list)


class PageListResponse(BaseModel):
    total: int
    pages: list[PageListItem]


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    max_pages: int = Field(default=10, ge=1, le=25)


class QueryCitation(BaseModel):
    slug: str
    title: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    citations: list[QueryCitation]
    pages_considered: int


class LintResponse(BaseModel):
    staleness: dict[str, Any]
    contradictions: dict[str, Any]


class StatusResponse(BaseModel):
    vault_root: str
    total_pages: int
    freshness_breakdown: dict[str, int]
    type_breakdown: dict[str, int]
    last_sync: dict[str, str | None]
    last_publish: str | None


class JobResponse(BaseModel):
    job_id: str
    status: str
    kind: str


class JobStatus(BaseModel):
    id: str
    kind: str
    status: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result: Any | None = None
    error: str | None = None


# Simple in-memory tracker for "last X at" values on /status. Updated by the
# background tasks on success.
_LAST_EVENTS: dict[str, str | None] = {
    "confluence_sync": None,
    "signoz_sync": None,
    "publish": None,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _page_to_response(page: WikiPage) -> WikiPageResponse:
    return WikiPageResponse(
        slug=getattr(page, "slug", ""),
        title=getattr(page, "title", "") or getattr(page, "slug", ""),
        type=str(getattr(page, "type", "") or "") or None,
        frontmatter=dict(getattr(page, "frontmatter", {}) or {}),
        body=getattr(page, "body", "") or "",
        path=str(getattr(page, "path", "")) if getattr(page, "path", None) else None,
    )


def _page_to_list_item(page: WikiPage) -> PageListItem:
    fm = dict(getattr(page, "frontmatter", {}) or {})
    tags_raw = fm.get("tags") or []
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    elif isinstance(tags_raw, (list, tuple, set)):
        tags = [str(t) for t in tags_raw if t]
    else:
        tags = []
    updated_at = fm.get("updated") or fm.get("updated_at") or fm.get("last_updated")
    return PageListItem(
        slug=getattr(page, "slug", ""),
        title=getattr(page, "title", "") or getattr(page, "slug", ""),
        type=str(getattr(page, "type", "") or "") or None,
        freshness=fm.get("freshness") or fm.get("status"),
        updated_at=str(updated_at) if updated_at is not None else None,
        tags=tags,
    )


async def _load_vault(engine: WikiEngine) -> list[WikiPage]:
    """Return all pages in the vault regardless of which method the engine exposes."""
    for method_name in ("load_vault", "load_all_pages", "list_pages", "all_pages"):
        method = getattr(engine, method_name, None)
        if callable(method):
            result = method()
            if hasattr(result, "__await__"):
                result = await result
            return list(result or [])
    raise HTTPException(status_code=503, detail="WikiEngine has no vault loader")


def _relevance_score(page: WikiPage, keywords: set[str]) -> int:
    if not keywords:
        return 0
    score = 0
    title = (getattr(page, "title", "") or "").lower()
    slug = (getattr(page, "slug", "") or "").lower()
    fm = getattr(page, "frontmatter", {}) or {}
    raw_tags = fm.get("tags") if isinstance(fm, dict) else None
    tags: list[str] = []
    if isinstance(raw_tags, (list, tuple, set)):
        tags = [str(t).lower() for t in raw_tags if t]
    elif isinstance(raw_tags, str):
        tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]

    for kw in keywords:
        if kw in title:
            score += 5
        if kw in slug:
            score += 3
        if any(kw in t for t in tags):
            score += 3
    return score


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/ingest", response_model=WikiPageResponse)
async def ingest(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(default=None),
    source_url: str | None = Body(default=None, embed=True),
) -> WikiPageResponse:
    """Ingest an uploaded file OR a remote URL into the wiki.

    Exactly one of ``file`` (multipart) or ``source_url`` (JSON body) must be
    provided. The call runs inline because ingestion is typically fast and the
    client wants the resulting page back immediately.
    """
    if file is None and not source_url:
        raise HTTPException(
            status_code=400, detail="Provide either a file upload or a source_url"
        )
    if file is not None and source_url:
        raise HTTPException(
            status_code=400, detail="Provide only one of file or source_url"
        )

    engine = get_engine()

    try:
        if file is not None:
            suffix = Path(file.filename or "upload").suffix or ".txt"
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix
            ) as tmp:
                tmp.write(await file.read())
                tmp_path = Path(tmp.name)
            try:
                page = await _ingest_via_engine(engine, path=tmp_path)
            finally:
                background_tasks.add_task(_safe_unlink, tmp_path)
        else:
            page = await _ingest_via_engine(engine, url=source_url or "")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("ingest failed")
        raise HTTPException(status_code=500, detail=f"ingest failed: {exc}") from exc

    if page is None:
        raise HTTPException(status_code=500, detail="ingest returned no page")
    return _page_to_response(page)


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        logger.warning("could not unlink temp upload %s", path)


async def _ingest_via_engine(
    engine: WikiEngine,
    *,
    path: Path | None = None,
    url: str | None = None,
) -> WikiPage | None:
    """Tolerate a few plausible WikiEngine method names so the router is
    not coupled to the exact final API the parallel agents pick."""
    if path is not None:
        for name in ("ingest_file", "ingest_path", "ingest"):
            fn = getattr(engine, name, None)
            if callable(fn):
                result = fn(path) if name != "ingest" else fn(path=path)
                if hasattr(result, "__await__"):
                    result = await result
                return result
    if url is not None:
        for name in ("ingest_url", "ingest"):
            fn = getattr(engine, name, None)
            if callable(fn):
                result = fn(url) if name != "ingest" else fn(url=url)
                if hasattr(result, "__await__"):
                    result = await result
                return result
    raise HTTPException(status_code=503, detail="WikiEngine has no ingest method")


@router.get("/pages", response_model=PageListResponse)
async def list_pages(
    type: str | None = Query(default=None, description="Filter by page type"),
    freshness: str | None = Query(default=None, description="Filter by freshness"),
) -> PageListResponse:
    """List pages currently in the vault, optionally filtered."""
    engine = get_engine()
    pages = await _load_vault(engine)

    def matches(p: WikiPage) -> bool:
        if type is not None:
            if str(getattr(p, "type", "") or "").lower() != type.lower():
                return False
        if freshness is not None:
            fm = getattr(p, "frontmatter", {}) or {}
            page_freshness = (fm.get("freshness") or fm.get("status") or "").lower()
            if page_freshness != freshness.lower():
                return False
        return True

    filtered = [p for p in pages if matches(p)]
    return PageListResponse(
        total=len(filtered),
        pages=[_page_to_list_item(p) for p in filtered],
    )


@router.get("/pages/{slug}", response_model=WikiPageResponse)
async def get_page(slug: str) -> WikiPageResponse:
    """Return a single page by slug."""
    engine = get_engine()
    # Prefer a direct lookup if the engine provides one.
    for name in ("get_page", "load_page", "read_page"):
        fn = getattr(engine, name, None)
        if callable(fn):
            try:
                page = fn(slug)
                if hasattr(page, "__await__"):
                    page = await page
            except FileNotFoundError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            except Exception:
                page = None
            if page is not None:
                return _page_to_response(page)

    # Fallback: scan the vault.
    for page in await _load_vault(engine):
        if getattr(page, "slug", None) == slug:
            return _page_to_response(page)
    raise HTTPException(status_code=404, detail=f"page not found: {slug}")


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Answer a natural-language question using the vault as context."""
    engine = get_engine()
    pages = await _load_vault(engine)
    if not pages:
        return QueryResponse(
            question=request.question,
            answer="The vault is empty — ingest some documents first.",
            citations=[],
            pages_considered=0,
        )

    keywords = {
        w.strip(".,!?;:()[]\"'").lower()
        for w in request.question.split()
        if len(w) >= 3
    }
    scored = sorted(
        pages, key=lambda p: _relevance_score(p, keywords), reverse=True
    )
    top = scored[: request.max_pages]

    client = _get_anthropic_client()
    context_blocks: list[str] = []
    for page in top:
        title = getattr(page, "title", "") or getattr(page, "slug", "")
        slug = getattr(page, "slug", "")
        body = getattr(page, "body", "") or ""
        if len(body) > 4_000:
            body = body[:4_000] + "\n[...truncated...]"
        context_blocks.append(
            f"### Page: {title} (slug: {slug})\n{body}"
        )
    context = "\n\n---\n\n".join(context_blocks) or "(no pages)"

    system = (
        "You are an SRE knowledge assistant answering questions from a living "
        "wiki. Cite page slugs in the form [[slug]] inline. If the wiki does "
        "not contain the answer, say so plainly — do not invent facts."
    )
    user = (
        f"Question: {request.question}\n\n"
        f"Relevant wiki pages:\n\n{context}\n\n"
        "Give a concise, grounded answer. End with a 'Sources:' line listing "
        "the slugs you used."
    )

    try:
        response = await client.messages.create(
            model=settings.model_name,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except Exception as exc:
        logger.exception("query: claude call failed")
        raise HTTPException(status_code=502, detail=f"claude call failed: {exc}") from exc

    answer = ""
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "text":
            answer += getattr(block, "text", "") or ""

    return QueryResponse(
        question=request.question,
        answer=answer.strip(),
        citations=[
            QueryCitation(
                slug=getattr(p, "slug", ""),
                title=getattr(p, "title", "") or getattr(p, "slug", ""),
            )
            for p in top
        ],
        pages_considered=len(top),
    )


@router.post("/lint", response_model=LintResponse)
async def lint() -> LintResponse:
    """Run both staleness and contradiction lint over the vault."""
    engine = get_engine()
    pages = await _load_vault(engine)

    staleness_payload: dict[str, Any] = {"available": False}
    if StalenessLinter is not None:
        try:
            linter = StalenessLinter(
                rules=DEFAULT_RULES,
                stale_threshold_days=settings.wiki_stale_threshold_days,
                archive_threshold_days=settings.wiki_archive_threshold_days,
            )
            report = await _maybe_await(linter.lint(pages))
            staleness_payload = _model_to_dict(report)
        except Exception as exc:
            logger.exception("lint: staleness failed")
            staleness_payload = {"available": True, "error": str(exc)}

    contradiction_payload: dict[str, Any] = {"available": False}
    if ContradictionDetector is not None:
        try:
            client = _get_anthropic_client()
            detector = ContradictionDetector(
                anthropic_client=client,
                model=settings.wiki_contradiction_model,
            )
            report = await detector.scan_vault(pages)
            contradiction_payload = _model_to_dict(report)
        except HTTPException:
            contradiction_payload = {
                "available": False,
                "error": "anthropic client unavailable",
            }
        except Exception as exc:
            logger.exception("lint: contradiction failed")
            contradiction_payload = {"available": True, "error": str(exc)}

    return LintResponse(
        staleness=staleness_payload,
        contradictions=contradiction_payload,
    )


@router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    """Report wiki health: page counts, freshness, last sync timestamps."""
    engine = get_engine()
    pages = await _load_vault(engine)

    freshness_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for page in pages:
        fm = getattr(page, "frontmatter", {}) or {}
        fresh = (fm.get("freshness") or fm.get("status") or "unknown").lower()
        freshness_counts[fresh] = freshness_counts.get(fresh, 0) + 1
        ptype = str(getattr(page, "type", "") or "unknown").lower()
        type_counts[ptype] = type_counts.get(ptype, 0) + 1

    return StatusResponse(
        vault_root=str(settings.wiki_vault_root),
        total_pages=len(pages),
        freshness_breakdown=freshness_counts,
        type_breakdown=type_counts,
        last_sync={
            "confluence": _LAST_EVENTS.get("confluence_sync"),
            "signoz": _LAST_EVENTS.get("signoz_sync"),
        },
        last_publish=_LAST_EVENTS.get("publish"),
    )


@router.post("/sync/confluence", response_model=JobResponse)
async def sync_confluence(background_tasks: BackgroundTasks) -> JobResponse:
    """Kick off a Confluence sync in the background."""
    if ConfluenceSync is None or ConfluenceConfig is None:
        raise HTTPException(status_code=503, detail="Confluence sync module not available")
    if not settings.confluence_base_url or not settings.confluence_api_token:
        raise HTTPException(
            status_code=400, detail="Confluence is not configured in settings"
        )

    engine = get_engine()
    job_id = _new_job("confluence_sync")
    background_tasks.add_task(_run_confluence_sync, job_id, engine)
    return JobResponse(job_id=job_id, status="pending", kind="confluence_sync")


async def _run_confluence_sync(job_id: str, engine: WikiEngine) -> None:
    _mark_started(job_id)
    try:
        config = ConfluenceConfig(
            base_url=settings.confluence_base_url,
            space_key=settings.confluence_space_key,
            email=settings.confluence_email,
            api_token=settings.confluence_api_token,
        )
        sync = ConfluenceSync(config=config, engine=engine)
        result = await sync.sync()
        _LAST_EVENTS["confluence_sync"] = datetime.now(timezone.utc).isoformat()
        _mark_finished(job_id, _model_to_dict(result))
    except Exception as exc:
        logger.exception("confluence sync failed")
        _mark_failed(job_id, str(exc))


@router.post("/sync/signoz", response_model=JobResponse)
async def sync_signoz(background_tasks: BackgroundTasks) -> JobResponse:
    """Kick off a SigNoz sync in the background."""
    if SignozSync is None or SignozConfig is None:
        raise HTTPException(status_code=503, detail="SigNoz sync module not available")
    if not settings.signoz_base_url or not settings.signoz_api_key:
        raise HTTPException(
            status_code=400, detail="SigNoz is not configured in settings"
        )

    engine = get_engine()
    job_id = _new_job("signoz_sync")
    background_tasks.add_task(_run_signoz_sync, job_id, engine)
    return JobResponse(job_id=job_id, status="pending", kind="signoz_sync")


async def _run_signoz_sync(job_id: str, engine: WikiEngine) -> None:
    _mark_started(job_id)
    try:
        config = SignozConfig(
            base_url=settings.signoz_base_url,
            api_key=settings.signoz_api_key,
            lookback_days=settings.signoz_lookback_days,
        )
        sync = SignozSync(config=config, engine=engine)
        result = await sync.sync()
        _LAST_EVENTS["signoz_sync"] = datetime.now(timezone.utc).isoformat()
        _mark_finished(job_id, _model_to_dict(result))
    except Exception as exc:
        logger.exception("signoz sync failed")
        _mark_failed(job_id, str(exc))


@router.post("/publish", response_model=JobResponse)
async def publish(background_tasks: BackgroundTasks) -> JobResponse:
    """Publish the vault to the configured git remote in the background."""
    if Publisher is None or PublisherConfig is None:
        raise HTTPException(status_code=503, detail="Publisher module not available")
    job_id = _new_job("publish")
    background_tasks.add_task(_run_publish, job_id)
    return JobResponse(job_id=job_id, status="pending", kind="publish")


async def _run_publish(job_id: str) -> None:
    _mark_started(job_id)
    try:
        config = PublisherConfig(
            vault_root=settings.wiki_vault_root,
            remote_url=settings.wiki_remote_url,
            author_name=settings.wiki_git_author_name,
            author_email=settings.wiki_git_author_email,
            auto_push=settings.wiki_auto_push,
        )
        publisher = Publisher(config=config)
        result = await _maybe_await(publisher.publish())
        _LAST_EVENTS["publish"] = datetime.now(timezone.utc).isoformat()
        _mark_finished(job_id, _model_to_dict(result))
    except Exception as exc:
        logger.exception("publish failed")
        _mark_failed(job_id, str(exc))


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str) -> JobStatus:
    """Look up the status of a background sync or publish job."""
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
    return JobStatus(**job)


# ---------------------------------------------------------------------------
# Small internal utilities
# ---------------------------------------------------------------------------


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


def _model_to_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception:
        return {"repr": repr(obj)}

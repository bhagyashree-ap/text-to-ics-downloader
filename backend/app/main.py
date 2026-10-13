"""FastAPI service: paste text -> extract -> validate -> review -> download .ics."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .config import settings
from .extractor import extract
from .gcal import google_calendar_link
from .ics_builder import build_ics
from .schema import ExtractRequest, ExtractResponse, IcsRequest
from .validator import validate_events

app = FastAPI(
    title="Text → Calendar",
    description="Paste text, get a downloadable .ics / .ical calendar file.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_enabled": settings.llm_enabled,
        "model": settings.LLM_MODEL if settings.llm_enabled else None,
    }


@app.post("/extract", response_model=ExtractResponse)
def extract_events(req: ExtractRequest):
    """Extract and normalize events from pasted text. Returns events for review."""
    raw, used_llm = extract(req.text, req.timezone, req.locale)
    events = validate_events(raw.events, req.timezone)

    # Attach a Google Calendar link to each event (frontend may surface it).
    enriched = []
    for ev in events:
        item = ev.model_dump()
        item["google_calendar_link"] = google_calendar_link(ev)
        enriched.append(item)

    return {"events": enriched, "used_llm": used_llm}


@app.post("/ics")
def download_ics(req: IcsRequest):
    """Build the .ics file from (possibly user-edited) events and return it for download."""
    ics_text = build_ics(req.events, calendar_name=req.calendar_name)
    filename = _safe_filename(req.calendar_name) + ".ics"
    return Response(
        content=ics_text,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _safe_filename(name: str) -> str:
    # Keep alphanumerics, spaces, dashes, underscores; drop everything else.
    safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else " " for c in name)
    safe = "_".join(safe.split())
    # If nothing meaningful remains (e.g. only punctuation), fall back.
    if not safe.strip("_-"):
        return "events"
    return safe

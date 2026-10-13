"""FastAPI application entry point (spec sections 4.1, 17, 23).

The gateway exposes the external HTTP API and talks to internal gRPC services.
Health/readiness endpoints included. OpenAPI docs served at /docs.
"""
from __future__ import annotations

import grpc
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .core.config import settings
from .core.logging import configure_logging, log

configure_logging(settings.LOG_LEVEL)

app = FastAPI(
    title="Chronos AI — Universal Calendar Event Generator",
    description="Convert arbitrary text into downloadable iCalendar (.ics) files.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "env": settings.APP_ENV, "mock_mode": settings.mock_mode}


@app.get("/api/v1/ready")
def ready():
    """Readiness: can we reach the gRPC server?"""
    try:
        channel = grpc.insecure_channel(settings.GRPC_AI_EXTRACTION_TARGET)
        grpc.channel_ready_future(channel).result(timeout=2)
        grpc_ok = True
    except Exception:
        grpc_ok = False
    status = "ready" if grpc_ok else "degraded"
    return {"status": status, "grpc": grpc_ok}


@app.on_event("startup")
def _startup():
    log.info("Chronos AI gateway starting (mock_mode=%s)", settings.mock_mode)

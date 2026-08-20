"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .routers.api import router
from .store import ArtifactsMissing, store

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
log = logging.getLogger("rsf")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model once, at start-up, so no request pays for it."""
    try:
        store.warm()
        app.state.ready = True
    except ArtifactsMissing as exc:
        app.state.ready = False
        app.state.error = str(exc)
        log.error("starting WITHOUT a model: %s", exc)
    yield


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=(
        "28-day-ahead unit sales forecasting for the M5 retail dataset, plus the "
        "analytics behind the dashboard. The model is a direct (non-recursive) "
        "LightGBM regressor; every feature it uses is knowable 28 days in advance."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["ops"])
def health():
    ready = getattr(app.state, "ready", False)
    body = {"status": "ok" if ready else "degraded", "model_loaded": ready}
    if not ready:
        body["error"] = getattr(app.state, "error", "artifacts not loaded")
        return JSONResponse(body, status_code=503)
    body["series_served"] = len(store.series_meta)
    body["last_observed_date"] = store.metadata["last_observed_date"]
    return body


@app.get("/", tags=["ops"])
def root():
    return {"service": settings.api_title, "version": settings.api_version, "docs": "/docs"}

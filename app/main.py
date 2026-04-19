"""
Reading Difficulty Transformer — FastAPI Application Entry Point.

A local-first tool that analyzes and transforms text reading difficulty
using traditional readability formulas and Ollama-powered AI.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.semantic_similarity import preload_model

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Startup: Preload the sentence-transformers model so it's ready
    for immediate use by the /transform and /simplify endpoints.
    Shutdown: No cleanup needed (model stays in memory).
    """
    # Startup
    logger.info("Starting Reading Difficulty Transformer...")
    try:
        loaded = preload_model()
        if loaded:
            logger.info("✓ Semantic similarity model preloaded at startup")
        else:
            logger.warning(
                "⚠ Semantic similarity model failed to load — "
                "scores will use fallback value"
            )
    except Exception as e:
        logger.warning("Model preload raised exception (non-fatal): %s", e)

    yield

    # Shutdown (nothing to do)
    logger.info("Shutting down Reading Difficulty Transformer...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Analyze and transform text reading difficulty — locally, privately.",
    lifespan=lifespan,
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Register API routes under /api
app.include_router(api_router, prefix="/api", tags=["analysis"])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main single-page UI."""
    return templates.TemplateResponse(request, "index.html")

"""
Reading Difficulty Transformer — FastAPI Application Entry Point.

A local-first tool that analyzes and transforms text reading difficulty
using traditional readability formulas and Ollama-powered AI.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router as api_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Analyze and transform text reading difficulty — locally, privately.",
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Register API routes under /api
app.include_router(api_router, prefix="/api", tags=["analysis"])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main single-page UI."""
    return templates.TemplateResponse("index.html", {"request": request})

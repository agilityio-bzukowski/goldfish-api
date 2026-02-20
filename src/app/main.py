"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import projects, tags, tasks
from app.core.config import settings

PREFIX = "/api"

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

# CORS: Vite dev server (1420) + Tauri webview origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "tauri://localhost",  # Tauri 2 webview origin when loading dev URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tags.router, prefix=PREFIX)
app.include_router(tasks.router, prefix=PREFIX)
app.include_router(projects.router, prefix=PREFIX)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}

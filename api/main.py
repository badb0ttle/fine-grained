"""FastAPI application entry point."""

import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from api.config import CORS_ORIGINS
from api.db import check_db_health, ensure_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify DB is accessible. Shutdown: clean up."""
    health = check_db_health()
    if health["status"] == "error":
        print(f"⚠️  DB health check failed: {health['message']}")
    else:
        print(f"✅ DB OK — {health['article_count']} articles in {len(health['tables'])} tables")

    # Ensure API-specific schema exists
    created = ensure_schema()
    if created:
        print(f"📦 Schema ensured: {', '.join(created)}")
    yield
    print("👋 FastAPI shutting down")


app = FastAPI(
    title="AllOfAI API",
    description="Backend for ai.hjhai.xyz — curated AI intelligence",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,       # disable Swagger UI in production
    redoc_url=None,      # disable ReDoc in production
    openapi_url=None,    # disable OpenAPI schema in production
)

# ── CORS: allow frontend from GitHub Pages ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ── Request logging middleware ──
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    # Avoid logging health checks excessively
    if request.url.path not in ("/health", "/"):
        print(
            f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} "
            f"{request.method:6} {request.url.path:40} "
            f"→ {response.status_code} ({duration*1000:.0f}ms)"
        )
    return response


# ── Health check ──
@app.get("/health", tags=["system"])
def health():
    """Health check — returns DB status and article count."""
    db_health = check_db_health()
    return {
        "service": "AllOfAI API",
        "status": "healthy" if db_health["status"] == "ok" else "unhealthy",
        "db": db_health,
    }


# ── Root (friendly redirect for browser) ──
@app.get("/", tags=["system"])
def root():
    return {
        "service": "AllOfAI API",
        "docs": "/docs",
        "version": "1.0.0",
    }


# ── Public routes (read-only, no auth) ──
from api.routers import public
app.include_router(public.router)

# ── Phase 3: Internal routes (write, auth-required) ──
from api.routers import internal
app.include_router(internal.router)

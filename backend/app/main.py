from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    HAS_SLOWAPI = True
except ImportError:
    HAS_SLOWAPI = False
    class Limiter:
        def __init__(self, *args, **kwargs): pass
        def limit(self, *args, **kwargs):
            return lambda fn: fn
    class RateLimitExceeded(Exception): pass
    _rate_limit_exceeded_handler = None
    get_remote_address = lambda req: "127.0.0.1"

from backend.app.core.config import settings
from backend.app.api import ai, analytics, assessments, auth, learning, profile, schedule, targets

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # App startup logic
    yield
    # App shutdown logic


app = FastAPI(
    title="Personalized Learning Path Dashboard (RCT-GAT) API",
    description="Backend orchestration for adaptive diagnostics, root-cause prerequisite tracing, and learning path scheduling.",
    version="1.0.0",
    lifespan=lifespan,
)

# Slowapi rate limiter setup
app.state.limiter = limiter
if HAS_SLOWAPI and _rate_limit_exceeded_handler:
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # configure specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health checks
@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "palp-api",
        "version": "1.0.0",
        "env": settings.ENV,
    }


# Include Routers
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(targets.router, prefix="/api/targets", tags=["Targets"])
app.include_router(profile.router, prefix="/api/me", tags=["Profile"])
app.include_router(assessments.router, prefix="/api/assessments", tags=["Assessments"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(learning.router, prefix="/api/learning", tags=["Learning Path"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["Schedule"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Assistant"])

# Mount built frontend dist if available (SPA Fallback)
import os
from fastapi.responses import FileResponse

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


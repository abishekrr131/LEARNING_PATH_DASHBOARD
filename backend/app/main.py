from __future__ import annotations
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
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

from backend.app.api import (
    ai,
    analytics,
    assessments,
    auth,
    diagnostic,
    learning,
    profile,
    schedule,
    targets,
    weekly_test,
)
from backend.app.core.config import settings

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


import asyncio
import logging
from backend.app.db.session import engine, SessionLocal
from backend.app.models.core import Base
from backend.app.services.weekly_adaptation import run_scheduled_weekly_adaptation_job

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # App startup logic: ensure database tables exist
    Base.metadata.create_all(bind=engine)

    # Auto-seed database if empty of targets
    try:
        from backend.app.models.core import CareerTarget
        with SessionLocal() as db_session:
            target_count = db_session.query(CareerTarget).count()
            if target_count == 0:
                logger.info("Database has no targets seeded. Running auto-seeding...")
                from database.seed.seed_all import seed_database
                seed_database(db_session, auto_approve=True)
                db_session.commit()
                logger.info("Database auto-seeded successfully with all 7 targets.")
    except Exception as exc:
        logger.error("Auto-seeding during startup failed: %s", exc)

    # Start recurring background scheduler task for weekly adaptation
    async def scheduled_weekly_adaptation_worker():
        while True:
            try:
                # Sleep interval between scheduler sweeps (checks every hour)
                await asyncio.sleep(3600)
                with SessionLocal() as db:
                    run_scheduled_weekly_adaptation_job(db)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error during scheduled weekly adaptation: %s", exc)
                await asyncio.sleep(60)

    worker_task = asyncio.create_task(scheduled_weekly_adaptation_worker())
    app.state.adaptation_worker_task = worker_task

    yield

    # App shutdown logic: gracefully cancel background worker
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health checks with structured observability
@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check():
    from sqlalchemy import select, func
    from backend.app.db.session import SessionLocal
    from backend.app.models.core import Skill, Concept, Question

    db_status = "unreachable"
    counts = {"skills": 0, "concepts": 0, "questions": 0}
    tables_seeded = False

    try:
        with SessionLocal() as s:
            counts["skills"] = s.scalar(select(func.count(Skill.id))) or 0
            counts["concepts"] = s.scalar(select(func.count(Concept.id))) or 0
            counts["questions"] = s.scalar(select(func.count(Question.id))) or 0
            db_status = "connected"
            tables_seeded = (counts["skills"] > 0 and counts["concepts"] > 0 and counts["questions"] > 0)
    except Exception as e:
        db_status = f"error: {str(e)}"

    gemini_configured = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here")

    from ai.gemini_client import get_verified_gemini_models, build_failover_order
    verified_models = get_verified_gemini_models() if gemini_configured else []
    failover_chain = build_failover_order(settings.GEMINI_MODEL, settings.GEMINI_FALLBACK_MODELS, verified_models) if gemini_configured else []

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "palp-api",
        "version": "1.0.0",
        "env": settings.ENV,
        "database": {
            "status": db_status,
            "seeded": tables_seeded,
            "counts": counts,
        },
        "gemini": {
            "status": "configured" if gemini_configured else "unconfigured",
            "configured": gemini_configured,
            "model": settings.GEMINI_MODEL,
            "verified_models_count": len(verified_models),
            "failover_models": failover_chain,
            "allow_bank_fallback": settings.ALLOW_BANK_FALLBACK,
        },
    }


@app.get("/health/gemini", tags=["Health"])
@app.get("/api/health/gemini", tags=["Health"])
def health_check_gemini():
    """Performs live model verification via ListModels and a minimal ping call to return active reachability status."""
    import time
    from ai.gemini_client import GeminiClient, get_verified_gemini_models, build_failover_order

    api_key = settings.GEMINI_API_KEY
    model_name = settings.GEMINI_MODEL

    if not api_key or api_key in ("your_gemini_api_key_here", ""):
        return JSONResponse(
            status_code=503,
            content={
                "status": "unconfigured",
                "configured": False,
                "model": model_name,
                "verified_available_models": [],
                "failover_order": [],
                "error": "GEMINI_API_KEY is not configured or is empty. Set GEMINI_API_KEY in .env.",
            },
        )

    verified_models = get_verified_gemini_models(api_key)
    failover_order = build_failover_order(model_name, settings.GEMINI_FALLBACK_MODELS, verified_models)

    t0 = time.perf_counter()
    try:
        client = GeminiClient(api_key=api_key, model_name=model_name)
        if not client.is_configured:
            raise RuntimeError("GeminiClient failed to initialize with provided key.")
        resp = client._client.models.generate_content(
            model=model_name,
            contents="ping",
            config={"max_output_tokens": 10, "temperature": 0.1, "timeout_sec": 15.0},
        )
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        resp_model = getattr(resp, "model_name", None)
        if isinstance(resp_model, str) and resp_model:
            active_model = resp_model
        elif isinstance(client.last_model_used, str) and client.last_model_used:
            active_model = client.last_model_used
        else:
            active_model = model_name
        return {
            "status": "ok",
            "configured": True,
            "model": active_model,
            "configured_model": model_name,
            "verified_available_models": verified_models,
            "failover_order": failover_order,
            "latency_ms": latency_ms,
            "response": (resp.text or "").strip()[:50],
        }
    except Exception as e:
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "configured": True,
                "model": model_name,
                "verified_available_models": verified_models,
                "failover_order": failover_order,
                "latency_ms": latency_ms,
                "error": str(e),
            },
        )


# Include Routers
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(targets.router, prefix="/api/targets", tags=["Targets"])
app.include_router(profile.router, prefix="/api/me", tags=["Profile"])
app.include_router(assessments.router, prefix="/api/assessments", tags=["Assessments"])
app.include_router(diagnostic.router, prefix="/api/diagnostic", tags=["Diagnostic"])
app.include_router(diagnostic.router, prefix="/diagnostic", tags=["Diagnostic"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(learning.router, prefix="/api/learning", tags=["Learning Path"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["Schedule"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Assistant"])
app.include_router(weekly_test.router, prefix="/api/weekly-test", tags=["Weekly Test"])
app.include_router(weekly_test.router, prefix="/weekly-test", tags=["Weekly Test"])

# Mount built frontend dist if available (SPA Fallback)
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    NO_CACHE_HEADERS = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Prevent 404 assets from returning index.html
        if full_path.startswith("assets/"):
            file_path = os.path.join(frontend_dist, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path, headers={"Cache-Control": "public, max-age=31536000, immutable"})
            raise HTTPException(status_code=404, detail="Asset not found")

        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(file_path):
            headers = NO_CACHE_HEADERS if full_path.endswith(".html") else {}
            return FileResponse(file_path, headers=headers)

        return FileResponse(os.path.join(frontend_dist, "index.html"), headers=NO_CACHE_HEADERS)


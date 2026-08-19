"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import scheduler
from app.core.config import settings
from app.core.database import Base, engine
from app.features.destinations.router import router as destinations_router
from app.features.mappings.router import router as mappings_router
from app.features.settings.router import router as settings_router
from app.features.sources.router import router as sources_router
from app.features.syncs.router import router as syncs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    - Creates database tables (in development; for production use Alembic).
    - Starts the background scheduler that triggers due syncs.
    - Disposes engine and stops the scheduler on shutdown.
    """
    # Startup: create tables if not exist (for development)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    scheduler_task = asyncio.create_task(scheduler.run_forever())

    yield

    # Shutdown: stop the scheduler and clean up connections
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS middleware (allow frontend development server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sources_router, prefix="/api/v1")
app.include_router(destinations_router, prefix="/api/v1")
app.include_router(mappings_router, prefix="/api/v1")
app.include_router(syncs_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": settings.APP_VERSION}

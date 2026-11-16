"""MAIRA Phase 1 Backend Application Entrypoint."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from app.api.v1 import api_v1_router
from app.core.config import get_settings
from app.core.database import check_db_connectivity, engine
from app.core.exceptions import setup_exception_handlers
from app.security.middleware import setup_middleware
from app.services.genai_service import GenAIClient

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("maira.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup checks and graceful shutdown."""
    logger.info(f"Starting {settings.APP_NAME} Backend [{settings.ENVIRONMENT}]...")

    # Database connectivity verification
    db_ok = await check_db_connectivity()
    if db_ok:
        logger.info("Successfully connected to PostgreSQL %s [schema: sch_con].", settings.DB_NAME)
    else:
        logger.warning("Could not establish immediate PostgreSQL connection on startup.")

    # Initialize persistent Gen AI client connection pool
    await GenAIClient.get_client()

    yield

    # Clean shutdown
    logger.info("Shutting down MAIRA backend, disposing connection pools...")
    await GenAIClient.close_client()
    await engine.dispose()
    logger.info("Connection pools closed.")


# Initialize FastAPI Application
app = FastAPI(
    title="MAIRA Phase 1 Institutional Backend",
    description="Production-grade conversational AI backend integrating PostgreSQL mira_db and local Gen AI RAG microservice.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 1. Register Middleware (CORS, Security Headers, Correlation ID)
setup_middleware(app)

# 2. Register Global Exception Handlers (Safe Error JSON)
setup_exception_handlers(app)

# 3. Mount API v1 Routers
app.include_router(api_v1_router)


# 4. Health, Liveness, and Readiness Checks
@app.get("/health", tags=["Health & Observability"], summary="Application Health Check")
async def health_check():
    """System health check endpoint indicating service and database status."""
    db_connected = await check_db_connectivity()
    overall_status = "healthy" if db_connected else "degraded"

    return JSONResponse(
        status_code=status.HTTP_200_OK if db_connected else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": overall_status,
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0",
            "database_connected": db_connected,
        },
    )


@app.get("/health/live", tags=["Health & Observability"], summary="Liveness Probe")
async def liveness_probe():
    """Kubernetes/Systemd liveness probe confirming process is responsive."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "live"},
    )


@app.get("/health/ready", tags=["Health & Observability"], summary="Readiness Probe")
async def readiness_probe():
    """Readiness probe checking database connectivity."""
    db_ok = await check_db_connectivity()
    if not db_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database": "disconnected"},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ready", "database": "connected"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

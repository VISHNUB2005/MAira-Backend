"""Development server launcher with preflight environment checks."""

import asyncio
from pathlib import Path
import sys

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from app.core.config import get_settings
from app.core.database import check_db_connectivity

settings = get_settings()


def preflight_checks() -> bool:
    print(f"Running preflight checks for {settings.APP_NAME} [{settings.ENVIRONMENT}]...")
    try:
        connected = asyncio.run(check_db_connectivity())
        if not connected:
            print("[WARN] Database connection failed. Verify PostgreSQL service and .env settings.")
            return False
        print("[OK] PostgreSQL connection verified.")
    except Exception as e:
        print(f"[ERROR] Database preflight exception: {e}")
        return False

    if len(settings.JWT_SECRET_KEY.encode("utf-8")) < 32:
        print("[ERROR] JWT_SECRET_KEY is too short (must be >= 32 bytes).")
        return False
    print("[OK] JWT configuration verified.")

    return True


if __name__ == "__main__":
    if not preflight_checks():
        print("Starting in degraded mode or aborting...")
    
    print(f"\nStarting development server on http://{settings.HOST}:{settings.PORT}")
    print(f"OpenAPI Documentation: http://{settings.HOST}:{settings.PORT}/docs\n")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

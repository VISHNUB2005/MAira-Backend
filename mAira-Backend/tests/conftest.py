"""Pytest configuration and global test fixtures with strict test database isolation."""

import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# ==============================================================================
# 1. HARD SAFETY GUARD FOR TEST DATABASE ISOLATION
# ==============================================================================

# Force test configuration
if os.environ.get("ENVIRONMENT") == "production":
    raise RuntimeError("CRITICAL SAFETY VIOLATION: Automated tests are strictly prohibited from executing in production environment!")

os.environ["ENVIRONMENT"] = "test"
os.environ["EMAIL_PROVIDER"] = "mock"
os.environ["JWT_SECRET_KEY"] = "maira_test_suite_super_secret_jwt_key_32bytes_min!"
os.environ["RATE_LIMIT_ENABLED"] = "false"

# Verify target test database
test_db_name = os.environ.get("TEST_DB_NAME", "mira_test_db")
if test_db_name == "mira_db":
    raise RuntimeError(
        "CRITICAL SAFETY VIOLATION: Automated tests are strictly prohibited from connecting to "
        "the institutional database 'mira_db'! Target must be an isolated test database (e.g. 'mira_test_db')."
    )

from app.core.config import get_settings

settings = get_settings()

test_db_url = os.environ.get(
    "TEST_DATABASE_URL",
    f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{test_db_name}",
)

if "mira_db" in test_db_url and "mira_test_db" not in test_db_url:
    raise RuntimeError(
        f"CRITICAL SAFETY VIOLATION: Resolved test database URL '{test_db_url}' targets "
        "institutional database 'mira_db'! Tests aborted."
    )

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.admin import Admin
from app.models.user import User
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository
from app.services.email_service import MockEmailProvider

# Engine strictly connected to isolated test database with NullPool
test_engine = create_async_engine(
    test_db_url,
    echo=False,
    poolclass=NullPool,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest_asyncio.fixture
async def db_session():
    """Yields an isolated database session in mira_test_db that executes within a transaction and rolls back."""
    connection = await test_engine.connect()
    trans = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Async HTTP test client with overridden database dependency bound to mira_test_db."""
    MockEmailProvider.clear()

    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_student_user(db_session: AsyncSession) -> User:
    """Fixture providing an active registered student user in mira_test_db."""
    user_repo = UserRepository(db_session)
    email = "test.student@example.com"
    user = await user_repo.get_user_by_email(email)
    if not user:
        user = await user_repo.create_user(email=email, user_type="STUDENT", status="ACTIVE")

    pw_hash = hash_password("ValidPassword123!")
    user.password_hash = pw_hash
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_admin_user(db_session: AsyncSession) -> Admin:
    """Fixture providing an active registered admin user in mira_test_db."""
    user_repo = UserRepository(db_session)
    email = "test.admin@example.com"
    admin = await user_repo.get_admin_by_email(email)
    if not admin:
        admin = Admin(
            name="Test Admin",
            email=email,
            status="ACTIVE",
            password_hash=hash_password("AdminPassword123!"),
        )
        db_session.add(admin)
        await db_session.flush()
    else:
        admin.password_hash = hash_password("AdminPassword123!")
        await db_session.flush()
    return admin


@pytest_asyncio.fixture
async def student_auth_headers(db_session: AsyncSession, test_student_user: User) -> dict:
    """Returns Bearer Authorization headers for the test student."""
    session_repo = SessionRepository(db_session)
    from datetime import datetime, timedelta, timezone
    import secrets
    from app.core.security import hash_refresh_token

    raw_token = secrets.token_urlsafe(64)
    session_rec = await session_repo.create_session(
        account_type="USER",
        account_id=test_student_user.user_id,
        refresh_token_hash=hash_refresh_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    token = create_access_token(
        user_id=test_student_user.user_id,
        session_id=str(session_rec.session_id),
        email=test_student_user.email,
        role="STUDENT",
        account_type="USER",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(db_session: AsyncSession, test_admin_user: Admin) -> dict:
    """Returns Bearer Authorization headers for the test admin."""
    session_repo = SessionRepository(db_session)
    from datetime import datetime, timedelta, timezone
    import secrets
    from app.core.security import hash_refresh_token

    raw_token = secrets.token_urlsafe(64)
    session_rec = await session_repo.create_session(
        account_type="ADMIN",
        account_id=test_admin_user.admin_id,
        refresh_token_hash=hash_refresh_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    token = create_access_token(
        user_id=test_admin_user.admin_id,
        session_id=str(session_rec.session_id),
        email=test_admin_user.email,
        role="ADMIN",
        account_type="ADMIN",
    )
    return {"Authorization": f"Bearer {token}"}

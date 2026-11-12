from fastapi import FastAPI

from modules.m_auth.m_auth_password_routes import router as password_router
from modules.m_auth.m_auth_password_setup import PasswordSetupService
from modules.m_auth.m_auth_password_repository import PostgresUserPasswordRepository
from modules.m_auth.m_auth_postgres import connect_to_database
from modules.m_auth.m_auth_registration_token import RegistrationTokenVerifier

app = FastAPI(
    title="MAira Backend",
    description="Backend services for the MAira institutional conversational platform",
    version="1.0.0",
)


@app.on_event("startup")
def configure_password_setup():
    token_verifier = RegistrationTokenVerifier()
    user_repository = PostgresUserPasswordRepository(connect_to_database)

    app.state.password_setup_service = PasswordSetupService(
        token_verifier,
        user_repository,
    )


app.include_router(password_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

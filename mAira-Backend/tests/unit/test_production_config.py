"""Unit tests demonstrating startup failure for missing or insecure production configuration."""

import pytest
from app.core.config import Settings


def test_production_rejects_insecure_fallback_jwt_secret():
    with pytest.raises(ValueError, match="Production JWT_SECRET_KEY must not use development fallback values"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="dev_insecure_key_must_be_set_in_env_file_32bytes!",
            GENAI_SERVICE_SECRET="production-genai-secret-key-16b",
            DB_PASSWORD="real_prod_password_123!",
            MFA_ENABLED=True,
            DEBUG=False,
            EMAIL_PROVIDER="smtp",
            EMAIL_HOST="smtp.institution.edu",
            EMAIL_USERNAME="mailer",
            EMAIL_PASSWORD="smtp_password_123",
            CORS_ALLOW_ORIGINS_RAW="https://maira.institution.edu",
        )


def test_production_rejects_short_jwt_secret():
    with pytest.raises(ValueError, match="at least 32 bytes"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="too_short",
            GENAI_SERVICE_SECRET="production-genai-secret-key-16b",
            DB_PASSWORD="real_prod_password_123!",
            MFA_ENABLED=True,
            DEBUG=False,
            EMAIL_PROVIDER="smtp",
            EMAIL_HOST="smtp.institution.edu",
            EMAIL_USERNAME="mailer",
            EMAIL_PASSWORD="smtp_password_123",
            CORS_ALLOW_ORIGINS_RAW="https://maira.institution.edu",
        )


def test_production_rejects_debug_enabled():
    with pytest.raises(ValueError, match="DEBUG mode must be disabled in production"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="A_Valid_Production_Secret_Key_With_High_Entropy_256bits!",
            GENAI_SERVICE_SECRET="production-genai-secret-key-16b",
            DB_PASSWORD="real_prod_password_123!",
            MFA_ENABLED=True,
            DEBUG=True,
            EMAIL_PROVIDER="smtp",
            EMAIL_HOST="smtp.institution.edu",
            EMAIL_USERNAME="mailer",
            EMAIL_PASSWORD="smtp_password_123",
            CORS_ALLOW_ORIGINS_RAW="https://maira.institution.edu",
        )


def test_production_rejects_mfa_disabled():
    with pytest.raises(ValueError, match="MFA_ENABLED is mandatory and must be True in production"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="A_Valid_Production_Secret_Key_With_High_Entropy_256bits!",
            GENAI_SERVICE_SECRET="production-genai-secret-key-16b",
            DB_PASSWORD="real_prod_password_123!",
            MFA_ENABLED=False,
            DEBUG=False,
            EMAIL_PROVIDER="smtp",
            EMAIL_HOST="smtp.institution.edu",
            EMAIL_USERNAME="mailer",
            EMAIL_PASSWORD="smtp_password_123",
            CORS_ALLOW_ORIGINS_RAW="https://maira.institution.edu",
        )


def test_production_rejects_missing_genai_secret():
    with pytest.raises(ValueError, match="GENAI_SERVICE_SECRET is mandatory in production"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="A_Valid_Production_Secret_Key_With_High_Entropy_256bits!",
            GENAI_SERVICE_SECRET="",
            DB_PASSWORD="real_prod_password_123!",
            MFA_ENABLED=True,
            DEBUG=False,
            EMAIL_PROVIDER="smtp",
            EMAIL_HOST="smtp.institution.edu",
            EMAIL_USERNAME="mailer",
            EMAIL_PASSWORD="smtp_password_123",
            CORS_ALLOW_ORIGINS_RAW="https://maira.institution.edu",
        )


def test_production_rejects_mock_email_provider():
    with pytest.raises(ValueError, match="EMAIL_PROVIDER cannot be 'mock' in production"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="A_Valid_Production_Secret_Key_With_High_Entropy_256bits!",
            GENAI_SERVICE_SECRET="production-genai-secret-key-16b",
            DB_PASSWORD="real_prod_password_123!",
            MFA_ENABLED=True,
            DEBUG=False,
            EMAIL_PROVIDER="mock",
            CORS_ALLOW_ORIGINS_RAW="https://maira.institution.edu",
        )


def test_production_rejects_incomplete_smtp_credentials():
    with pytest.raises(ValueError, match="EMAIL_HOST, EMAIL_USERNAME, and EMAIL_PASSWORD are required"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="A_Valid_Production_Secret_Key_With_High_Entropy_256bits!",
            GENAI_SERVICE_SECRET="production-genai-secret-key-16b",
            DB_PASSWORD="real_prod_password_123!",
            MFA_ENABLED=True,
            DEBUG=False,
            EMAIL_PROVIDER="smtp",
            EMAIL_HOST="smtp.institution.edu",
            EMAIL_USERNAME="",  # Missing username
            EMAIL_PASSWORD="",
            CORS_ALLOW_ORIGINS_RAW="https://maira.institution.edu",
        )


def test_production_rejects_wildcard_cors():
    with pytest.raises(ValueError, match="Wildcard '\\*' CORS origin is strictly forbidden in production"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="A_Valid_Production_Secret_Key_With_High_Entropy_256bits!",
            GENAI_SERVICE_SECRET="production-genai-secret-key-16b",
            DB_PASSWORD="real_prod_password_123!",
            MFA_ENABLED=True,
            DEBUG=False,
            EMAIL_PROVIDER="smtp",
            EMAIL_HOST="smtp.institution.edu",
            EMAIL_USERNAME="mailer",
            EMAIL_PASSWORD="smtp_password_123",
            CORS_ALLOW_ORIGINS_RAW="https://maira.institution.edu,*",
        )


def test_production_rejects_test_db_name():
    with pytest.raises(ValueError, match="Production database name cannot be the test database name"):
        Settings(
            ENVIRONMENT="production",
            DB_NAME="mira_test_db",
            JWT_SECRET_KEY="A_Valid_Production_Secret_Key_With_High_Entropy_256bits!",
            GENAI_SERVICE_SECRET="production-genai-secret-key-16b",
            DB_PASSWORD="real_prod_password_123!",
            MFA_ENABLED=True,
            DEBUG=False,
            EMAIL_PROVIDER="smtp",
            EMAIL_HOST="smtp.institution.edu",
            EMAIL_USERNAME="mailer",
            EMAIL_PASSWORD="smtp_password_123",
            CORS_ALLOW_ORIGINS_RAW="https://maira.institution.edu",
        )


def test_production_accepts_valid_production_config():
    s = Settings(
        ENVIRONMENT="production",
        DB_NAME="mira_db",
        DB_PASSWORD="StrongProductionDbPassword123!",
        JWT_SECRET_KEY="A_Super_Secure_Institutional_JWT_Secret_Key_256Bits!",
        GENAI_SERVICE_SECRET="Institutional_GenAI_Microservice_Secret_32Chars!",
        MFA_ENABLED=True,
        DEBUG=False,
        EMAIL_PROVIDER="smtp",
        EMAIL_HOST="smtp.institution.edu",
        EMAIL_PORT=587,
        EMAIL_USERNAME="institutional_mailer",
        EMAIL_PASSWORD="ComplexSmtpPassword123!",
        CORS_ALLOW_ORIGINS_RAW="https://maira.institution.edu,https://admin.maira.institution.edu",
    )
    assert s.ENVIRONMENT == "production"
    assert s.MFA_ENABLED is True
    assert s.DEBUG is False
    assert len(s.cors_allow_origins) == 2

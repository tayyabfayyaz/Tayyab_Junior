"""T012: Backend configuration loader — reads env vars with defaults via Pydantic Settings."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Core
    fte_env: str = Field(default="development", alias="FTE_ENV")
    task_dir: str = Field(default="./tasks", alias="TASK_DIR")
    memory_dir: str = Field(default="./memory", alias="MEMORY_DIR")
    log_dir: str = Field(default="./logs", alias="LOG_DIR")

    # Auth
    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiry_minutes: int = Field(default=60, alias="JWT_EXPIRY_MINUTES")
    owner_email: str = Field(default="owner@example.com", alias="OWNER_EMAIL")
    owner_password_hash: str = Field(default="", alias="OWNER_PASSWORD_HASH")

    # Claude / Anthropic
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # Google Gemini
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    # Finance Assistant
    finance_files_dir: str = Field(default="./finance_files", alias="FINANCE_FILES_DIR")

    # Executor
    executor_poll_interval: int = Field(default=5, alias="EXECUTOR_POLL_INTERVAL_SECONDS")
    executor_max_retries: int = Field(default=3, alias="EXECUTOR_MAX_RETRIES")
    mcp_server_url: str = Field(default="http://mcp-server:8001", alias="MCP_SERVER_URL")

    # WhatsApp
    whatsapp_verify_token: str = Field(default="", alias="WHATSAPP_VERIFY_TOKEN")
    whatsapp_app_secret: str = Field(default="", alias="WHATSAPP_APP_SECRET")
    whatsapp_access_token: str = Field(default="", alias="WHATSAPP_ACCESS_TOKEN")
    whatsapp_phone_id: str = Field(default="", alias="WHATSAPP_PHONE_ID")
    whatsapp_owner_phone: str = Field(default="", alias="WHATSAPP_OWNER_PHONE")

    # Gmail
    gmail_client_id: str = Field(default="", alias="GMAIL_CLIENT_ID")
    gmail_client_secret: str = Field(default="", alias="GMAIL_CLIENT_SECRET")
    gmail_monitored_email: str = Field(default="", alias="GMAIL_MONITORED_EMAIL")

    # LinkedIn
    linkedin_client_id: str = Field(default="", alias="LINKEDIN_CLIENT_ID")
    linkedin_client_secret: str = Field(default="", alias="LINKEDIN_CLIENT_SECRET")
    linkedin_access_token: str = Field(default="", alias="LINKEDIN_ACCESS_TOKEN")

    # GitHub
    github_webhook_secret: str = Field(default="", alias="GITHUB_WEBHOOK_SECRET")

    # CEO Assistant / Reports
    reports_dir: str = Field(default="./reports", alias="REPORTS_DIR")
    ceo_email: str = Field(default="", alias="CEO_EMAIL")

    # Backend
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

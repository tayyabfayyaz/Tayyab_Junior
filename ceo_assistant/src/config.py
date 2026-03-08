"""CEO Assistant configuration — reads env vars via Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings


class CEOConfig(BaseSettings):
    ceo_email: str = Field(default="", alias="CEO_EMAIL")
    report_time: str = Field(default="18:00", alias="REPORT_TIME")  # HH:MM UTC
    task_dir: str = Field(default="./tasks", alias="TASK_DIR")
    memory_dir: str = Field(default="./memory", alias="MEMORY_DIR")
    log_dir: str = Field(default="./logs", alias="LOG_DIR")
    reports_dir: str = Field(default="./reports", alias="REPORTS_DIR")
    gmail_client_id: str = Field(default="", alias="GMAIL_CLIENT_ID")
    gmail_client_secret: str = Field(default="", alias="GMAIL_CLIENT_SECRET")
    gmail_monitored_email: str = Field(default="", alias="GMAIL_MONITORED_EMAIL")

    model_config = {"env_file": ".env", "extra": "ignore"}


config = CEOConfig()

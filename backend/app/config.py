from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Load backend/.env during local development.
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    database_url_env: str = os.environ.get(
        "DATABASE_URL",
        "",
    ).strip()

    database_path: str = os.environ.get(
        "SMS_ANALYZER_DB_PATH",
        str(BACKEND_DIR / "data" / "sms_analyzer.db"),
    )

    host: str = os.environ.get(
        "SMS_ANALYZER_HOST",
        "127.0.0.1",
    )

    port: int = int(
        os.environ.get(
            "SMS_ANALYZER_PORT",
            os.environ.get("PORT", "8000"),
        )
    )

    sample_data_dir: str = os.environ.get(
        "SMS_ANALYZER_SAMPLE_DATA_DIR",
        str(PROJECT_ROOT / "sample_data"),
    )

    default_currency: str = os.environ.get(
        "SMS_ANALYZER_CURRENCY",
        "KES",
    )

    debug: bool = (
        os.environ.get(
            "SMS_ANALYZER_DEBUG",
            "false",
        ).lower()
        == "true"
    )

    jwt_secret: str = os.environ.get(
        "SMS_ANALYZER_JWT_SECRET",
        "change-me-in-production",
    )

    jwt_algorithm: str = os.environ.get(
        "SMS_ANALYZER_JWT_ALGORITHM",
        "HS256",
    )

    jwt_expire_minutes: int = int(
        os.environ.get(
            "SMS_ANALYZER_JWT_EXPIRE_MINUTES",
            "10080",
        )
    )

    cors_origins: str = os.environ.get(
        "SMS_ANALYZER_CORS_ORIGINS",
        "",
    )

    @property
    def database_url(self) -> str:
        if self.database_url_env:
            return self.database_url_env

        db_path = Path(self.database_path)
        db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        return f"sqlite:///{db_path}"

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith(
            (
                "postgresql://",
                "postgres://",
                "postgresql+psycopg://",
            )
        )

    @property
    def extra_cors_origins(self) -> list[str]:
        if not self.cors_origins.strip():
            return []

        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
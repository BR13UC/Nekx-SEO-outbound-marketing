from dataclasses import dataclass
from pathlib import Path
import os


def _env_path(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default))).expanduser()


@dataclass(frozen=True)
class Settings:
    api_prefix: str = "/api/v1"
    db_path: Path = _env_path(
        "NEKX_DB_PATH",
        Path(__file__).resolve().parent.parent / "data" / "nekx.db",
    )
    leads_xlsx_path: Path = _env_path(
        "NEKX_LEADS_XLSX_PATH",
        Path(__file__).resolve().parent.parent / "data" / "groningen_food_drink_leads.xlsx",
    )
    case_insights_path: Path = _env_path(
        "NEKX_CASE_INSIGHTS_PATH",
        Path(__file__).resolve().parent / "data" / "case_insights.json",
    )
    email_mode: str = (os.getenv("NEKX_EMAIL_MODE", "gemini").strip().lower() or "gemini")
    email_fallback_mode: str = (
        os.getenv("NEKX_EMAIL_FALLBACK_MODE", "fallback").strip().lower() or "fallback"
    )
    gemini_api_key: str | None = os.getenv("GOOGLE_API_KEY")
    gemini_model: str = os.getenv("NEKX_GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    scheduler_config_path: Path = _env_path(
        "NEKX_SCHEDULER_CONFIG_PATH",
        Path(__file__).resolve().parent.parent / "data" / "scheduler_config.json",
    )

    @property
    def strict_email_mode(self) -> bool:
        return self.email_fallback_mode == "strict"


settings = Settings()

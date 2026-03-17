from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    api_prefix: str = "/api/v1"
    db_path: Path = Path(
        os.getenv(
            "NEKX_DB_PATH",
            str(Path(__file__).resolve().parent.parent / "data" / "nekx.db"),
        )
    )


settings = Settings()

from pydantic import BaseModel, Field


class SchedulerConfigOut(BaseModel):
    enabled: bool
    min_interval_minutes: int = Field(ge=0)
    log_level: str
    log_file_path: str


class SchedulerConfigPatchIn(BaseModel):
    enabled: bool | None = None
    min_interval_minutes: int | None = Field(default=None, ge=0)
    log_level: str | None = None
    log_file_path: str | None = None


class SchedulerRunIn(BaseModel):
    dry_run: bool = False
    mode: str = "live"

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..schemas.scheduler_schema import SchedulerConfigOut, SchedulerConfigPatchIn, SchedulerRunIn
from ..tools.run_outbound_cycle import DEFAULT_CONFIG, load_scheduler_config, run_cycle


router = APIRouter(tags=["scheduler"])


def _normalize_config(raw: dict) -> dict:
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(raw)
    cfg["enabled"] = bool(cfg.get("enabled", True))
    try:
        cfg["min_interval_minutes"] = max(0, int(cfg.get("min_interval_minutes", DEFAULT_CONFIG["min_interval_minutes"])))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="min_interval_minutes must be a non-negative integer")

    log_level = str(cfg.get("log_level", "INFO")).upper().strip()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise HTTPException(status_code=400, detail="log_level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL")
    cfg["log_level"] = log_level
    cfg["log_file_path"] = str(cfg.get("log_file_path") or DEFAULT_CONFIG["log_file_path"])
    return cfg


def _config_path() -> Path:
    return Path(settings.scheduler_config_path)


def _write_config_atomic(cfg: dict) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _extract_log_payload(line: str) -> dict | None:
    if "|" not in line:
        return None
    parts = line.split("|", 2)
    if len(parts) != 3:
        return None
    payload = parts[2].strip()
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _latest_scheduler_event(log_file_path: str, *, mode: str | None = None) -> dict | None:
    path = Path(log_file_path)
    if not path.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        path = (project_root / path).resolve()
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line in reversed(lines[-300:]):
        payload = _extract_log_payload(line)
        if not payload:
            continue
        if mode and payload.get("mode") != mode:
            continue
        timestamp = line.split("|", 1)[0].strip()
        return {"timestamp": timestamp, "event": payload.get("event"), "detail": payload}
    return None


@router.get("/scheduler/config", response_model=SchedulerConfigOut)
def scheduler_get_config() -> dict:
    try:
        cfg = load_scheduler_config(_config_path())
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="scheduler config JSON is invalid")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"unable to read scheduler config: {exc}")
    return _normalize_config(cfg)


@router.patch("/scheduler/config", response_model=SchedulerConfigOut)
def scheduler_patch_config(body: SchedulerConfigPatchIn) -> dict:
    try:
        current = load_scheduler_config(_config_path())
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="scheduler config JSON is invalid")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"unable to read scheduler config: {exc}")

    patch = body.model_dump(exclude_unset=True)
    current.update(patch)
    normalized = _normalize_config(current)
    _write_config_atomic(normalized)
    return normalized


@router.post("/scheduler/run")
def scheduler_run_once(body: SchedulerRunIn) -> dict:
    cfg = _normalize_config(load_scheduler_config(_config_path()))
    mode = (body.mode or "live").strip().lower()
    if mode not in {"live", "test"}:
        raise HTTPException(status_code=400, detail="mode must be 'live' or 'test'")
    effective_dry_run = body.dry_run or mode == "test"
    code = run_cycle(dry_run=effective_dry_run, mode=mode)
    latest_event = _latest_scheduler_event(cfg["log_file_path"], mode=mode)
    reason = None
    if latest_event and isinstance(latest_event.get("detail"), dict):
        reason = latest_event["detail"].get("reason")
    return {
        "ok": code == 0,
        "exit_code": code,
        "dry_run": effective_dry_run,
        "mode": mode,
        "latest_event": latest_event,
        "reason": reason,
    }

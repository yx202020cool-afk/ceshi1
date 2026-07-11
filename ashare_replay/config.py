from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        elif key != "extends":
            merged[key] = value
    return merged


def load_json_config(path: str | Path) -> dict[str, Any]:
    config_path = resolve_path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    parent = data.get("extends")
    if parent:
        base = load_json_config(parent)
        return _deep_merge(base, data)
    return data


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Settings:
    app_mode: str
    timezone: str
    database_url: str
    report_output_dir: Path
    config_path: Path
    log_level: str
    real_provider: str
    tushare_token: str
    llm_enabled: bool
    llm_provider: str
    llm_api_key: str
    app_password: str
    api_host: str
    api_port: int
    streamlit_port: int
    config: dict[str, Any]
    config_hash: str


def load_settings() -> Settings:
    _load_dotenv(PROJECT_ROOT / ".env")
    config_path = resolve_path(os.getenv("CONFIG_PATH", "configs/default_config.json"))
    config = load_json_config(config_path)
    timezone = os.getenv("APP_TIMEZONE", config.get("timezone", "Asia/Shanghai"))
    config["timezone"] = timezone
    config_hash = stable_hash(config)
    return Settings(
        app_mode=os.getenv("APP_MODE", "demo").strip().lower() or "demo",
        timezone=timezone,
        database_url=os.getenv("DATABASE_URL", "sqlite:///work/data/ashare_replay.sqlite3"),
        report_output_dir=resolve_path(os.getenv("REPORT_OUTPUT_DIR", "outputs/reports")),
        config_path=config_path,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        real_provider=os.getenv("REAL_PROVIDER", "akshare").strip().lower() or "akshare",
        tushare_token=os.getenv("TUSHARE_TOKEN", ""),
        llm_enabled=os.getenv("LLM_ENABLED", "false").lower() in {"1", "true", "yes"},
        llm_provider=os.getenv("LLM_PROVIDER", ""),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        app_password=os.getenv("APP_PASSWORD", "change-me"),
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("API_PORT", "8000")),
        streamlit_port=int(os.getenv("STREAMLIT_PORT", "8501")),
        config=config,
        config_hash=config_hash,
    )

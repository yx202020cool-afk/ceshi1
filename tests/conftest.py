from __future__ import annotations

import uuid

import pytest

from ashare_replay.config import PROJECT_ROOT, load_settings


@pytest.fixture()
def isolated_env(monkeypatch: pytest.MonkeyPatch):
    test_dir = PROJECT_ROOT / "work" / "test-runs" / uuid.uuid4().hex
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("APP_MODE", "demo")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_dir / 'test.sqlite3'}")
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(test_dir / "reports"))
    monkeypatch.setenv("CONFIG_PATH", "configs/default_config.json")
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Shanghai")
    for key in ["TUSHARE_TOKEN", "LLM_API_KEY"]:
        monkeypatch.setenv(key, "")
    return load_settings()

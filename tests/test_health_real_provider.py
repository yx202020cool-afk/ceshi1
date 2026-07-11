from __future__ import annotations

import builtins

from ashare_replay.config import load_settings
from ashare_replay.providers.akshare_provider import AkshareProvider
from ashare_replay.providers.tushare_provider import TushareProvider
from ashare_replay.services.health import provider_audit


def _block_akshare_import(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "akshare":
            raise ImportError("blocked in test")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_default_real_provider_is_free_akshare(monkeypatch):
    monkeypatch.setenv("APP_MODE", "real")
    monkeypatch.setenv("REAL_PROVIDER", "")
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    settings = load_settings()
    assert settings.real_provider == "akshare"


def test_akshare_missing_dependency_is_explicit(monkeypatch):
    _block_akshare_import(monkeypatch)
    monkeypatch.setenv("APP_MODE", "real")
    monkeypatch.setenv("REAL_PROVIDER", "akshare")
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    settings = load_settings()
    health = AkshareProvider(settings).health_check()
    assert health["status"] == "missing_dependency"
    assert health["uses_demo_data"] == 0
    assert health["readiness"]["token_required"] is False
    assert health["readiness"]["can_generate_real_report"] is False


def test_akshare_provider_audit_without_dependency(monkeypatch):
    _block_akshare_import(monkeypatch)
    monkeypatch.setenv("APP_MODE", "real")
    monkeypatch.setenv("REAL_PROVIDER", "akshare")
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    settings = load_settings()
    audit = provider_audit(settings, run_probes=False)
    assert audit["provider"] == "akshare"
    assert audit["token_required"] is False
    assert audit["can_generate_real_report"] is False
    assert audit["required_count"] >= 6
    assert audit["blocked_by"]
    assert all(row["status"] == "missing_dependency" for row in audit["capabilities"])


def test_real_provider_without_token_is_explicit(monkeypatch):
    monkeypatch.setenv("APP_MODE", "real")
    monkeypatch.setenv("REAL_PROVIDER", "tushare")
    monkeypatch.setenv("TUSHARE_TOKEN", "")
    settings = load_settings()
    health = TushareProvider(settings).health_check()
    assert health["status"] == "missing_token"
    assert health["uses_demo_data"] == 0
    assert health["readiness"]["can_generate_real_report"] is False


def test_provider_audit_lists_required_capabilities(monkeypatch):
    monkeypatch.setenv("APP_MODE", "real")
    monkeypatch.setenv("REAL_PROVIDER", "tushare")
    monkeypatch.setenv("TUSHARE_TOKEN", "")
    settings = load_settings()
    audit = provider_audit(settings, run_probes=False)
    assert audit["provider"] == "tushare"
    assert audit["can_generate_real_report"] is False
    assert audit["required_count"] >= 8
    assert audit["blocked_by"]
    assert all(row["status"] == "missing_token" for row in audit["capabilities"])

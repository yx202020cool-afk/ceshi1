from __future__ import annotations

from typing import Any

from ashare_replay.config import Settings
from ashare_replay.db import Database
from ashare_replay.providers import build_provider


def health_status(settings: Settings) -> dict[str, Any]:
    db = Database(settings.database_url, settings.timezone)
    db.init_db()
    provider = build_provider(settings)
    health = provider.health_check()
    db.upsert_provider_health(health)
    return {
        "app": "ok",
        "mode": settings.app_mode,
        "timezone": settings.timezone,
        "database": db.kind,
        "provider": health,
        "uses_demo_data": bool(health.get("uses_demo_data")),
    }


def provider_audit(settings: Settings, run_probes: bool = True) -> dict[str, Any]:
    provider = build_provider(settings)
    audit = getattr(provider, "audit_capabilities", None)
    if audit is None:
        return {
            "provider": provider.provider_name,
            "mode": provider.mode,
            "run_probes": False,
            "can_generate_real_report": provider.mode == "demo",
            "blocked_by": [],
            "capabilities": [],
            "message": "当前 Provider 没有额外权限自检要求。",
        }
    return audit(run_probes=run_probes)

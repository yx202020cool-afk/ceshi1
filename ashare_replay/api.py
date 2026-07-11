from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from ashare_replay.config import load_settings
from ashare_replay.constants import REPORT_TYPES
from ashare_replay.db import Database
from ashare_replay.services.health import health_status, provider_audit
from ashare_replay.services.ops import docker_environment_check
from ashare_replay.services.scheduler import run_manual_backfill
from ashare_replay.time_utils import parse_trade_date


def create_app() -> FastAPI:
    app = FastAPI(title="A 股每日全局复盘与板块资金分析系统", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return health_status(load_settings())

    @app.get("/provider/audit")
    def audit(no_probe: bool = Query(default=True)) -> dict[str, Any]:
        return provider_audit(load_settings(), run_probes=not no_probe)

    @app.get("/ops/check")
    def ops_check(no_compose_config: bool = Query(default=True)) -> dict[str, Any]:
        return docker_environment_check(run_compose_config=not no_compose_config)

    @app.get("/reports/latest")
    def latest(limit: int = Query(default=10, ge=1, le=100)) -> list[dict[str, Any]]:
        settings = load_settings()
        db = Database(settings.database_url, settings.timezone)
        db.init_db()
        return db.latest_reports(limit)

    @app.post("/reports/generate")
    def generate(
        trade_date: str = Query(default="today"),
        report_type: str = Query(default="POST_CLOSE_FINAL"),
    ) -> dict[str, Any]:
        if report_type not in REPORT_TYPES:
            raise HTTPException(status_code=400, detail="未知报告类型")
        settings = load_settings()
        parsed: date = parse_trade_date(trade_date, settings.timezone)
        try:
            return run_manual_backfill(settings, parsed, report_type)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc

    return app


app = create_app()
